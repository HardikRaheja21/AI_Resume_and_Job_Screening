const API_BASE = localStorage.getItem("api_base") || "http://127.0.0.1:8000";

const state = {
  results: [],
  lastPayload: null,
  sortDescending: true,
  selectedFiles: [],
  jobs: [],
  selectedJobId: null,
  currentPage: 1,
  pageSize: 8,
  selectedResumeId: null,
  interviewQuestionsById: {},
  interviewSessionsByResumeId: {},
};

function getToken() {
  return localStorage.getItem("jwt_token") || "";
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function handleUnauthorized(status) {
  if (status !== 401) return false;
  localStorage.removeItem("jwt_token");
  if (window.location.pathname.endsWith("/dashboard.html")) {
    window.location.href = "login.html";
  }
  return true;
}

function getErrorMessage(payload, fallback = "Request failed.") {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
  if (payload.error && typeof payload.error.message === "string") return payload.error.message;
  return fallback;
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (response.ok) return { ok: true, payload };
  return { ok: false, payload, status: response.status };
}

function setMessage(el, text, isError = false) {
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? "#b42318" : "#14532d";
}

function initLoginPage() {
  const signupBtn = document.getElementById("btn-signup");
  const loginBtn = document.getElementById("btn-login");
  if (!signupBtn && !loginBtn) return;

  signupBtn?.addEventListener("click", async () => {
    const email = document.getElementById("signup-email")?.value.trim();
    const password = document.getElementById("signup-password")?.value.trim();
    const msg = document.getElementById("signup-msg");

    if (!email || !password) {
      setMessage(msg, "Email and password are required.", true);
      return;
    }
    setMessage(msg, "Creating account...");

    const response = await fetch(`${API_BASE}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).catch(() => null);

    if (!response) {
      setMessage(msg, "Server not reachable.", true);
      return;
    }
    const result = await parseResponse(response);
    if (!result.ok) {
      handleUnauthorized(result.status);
      setMessage(msg, getErrorMessage(result.payload, "Signup failed."), true);
      return;
    }
    setMessage(msg, "Signup successful. You can log in now.");
  });

  loginBtn?.addEventListener("click", async () => {
    const email = document.getElementById("login-email")?.value.trim();
    const password = document.getElementById("login-password")?.value.trim();
    const msg = document.getElementById("login-msg");
    const tokenBox = document.getElementById("auth-token");

    if (!email || !password) {
      setMessage(msg, "Email and password are required.", true);
      return;
    }
    setMessage(msg, "Logging in...");

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).catch(() => null);

    if (!response) {
      setMessage(msg, "Server not reachable.", true);
      return;
    }
    const result = await parseResponse(response);
    if (!result.ok) {
      handleUnauthorized(result.status);
      setMessage(msg, getErrorMessage(result.payload, "Login failed."), true);
      return;
    }

    const token = result.payload.access_token || "";
    localStorage.setItem("jwt_token", token);
    if (tokenBox) tokenBox.value = token;
    setMessage(msg, "Login successful. Open Dashboard.");
  });
}

function updateWordCount() {
  const jdEl = document.getElementById("job-description");
  const countEl = document.getElementById("jd-word-count");
  if (!jdEl || !countEl) return;
  const wordCount = (jdEl.value.trim().match(/\S+/g) || []).length;
  countEl.textContent = `${wordCount} words`;
}

function renderFileList() {
  const fileList = document.getElementById("file-list");
  if (!fileList) return;
  if (!state.selectedFiles.length) {
    fileList.innerHTML = "";
    return;
  }
  fileList.innerHTML = state.selectedFiles
    .map((file) => `<div>${file.name} (${Math.ceil(file.size / 1024)} KB)</div>`)
    .join("");
}

function normalizeResults(results) {
  return [...results].sort((a, b) => {
    const av = Number(a?.score || 0);
    const bv = Number(b?.score || 0);
    return state.sortDescending ? bv - av : av - bv;
  });
}

function pagedResults(results) {
  const totalPages = Math.max(1, Math.ceil(results.length / state.pageSize));
  if (state.currentPage > totalPages) state.currentPage = totalPages;
  if (state.currentPage < 1) state.currentPage = 1;
  const start = (state.currentPage - 1) * state.pageSize;
  const end = start + state.pageSize;
  return {
    pageItems: results.slice(start, end),
    totalPages,
  };
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function renderBreakdownRows(scoreBreakdown = {}) {
  const rows = [
    ["Required", Number(scoreBreakdown.required_skill_score || 0)],
    ["Optional", Number(scoreBreakdown.optional_skill_score || 0)],
    ["Semantic", Number(scoreBreakdown.semantic_score || 0)],
    ["Experience", Number(scoreBreakdown.experience_score || 0)],
  ];
  return rows.map(([label, value]) => `
    <div class="score-row">
      <span>${escapeHtml(label)}</span>
      <div class="score-bar"><div class="score-bar-fill" style="width:${Math.max(0, Math.min(100, value * 100))}%"></div></div>
      <strong>${escapeHtml(formatPercent(value))}</strong>
    </div>
  `).join("");
}

function updateRankingSummary(results, jdSummary = "", jdAnalysis = null) {
  const summaryEl = document.getElementById("ranking-summary");
  const countEl = document.getElementById("dash-candidate-count");
  const jdPanel = document.getElementById("jd-analysis-panel");
  if (!summaryEl || !countEl || !jdPanel) return;

  const total = results.length;
  countEl.textContent = `${total} candidates loaded`;
  if (!total) {
    summaryEl.textContent = "No candidates yet. Run a match or load history.";
    jdPanel.innerHTML = `<div class="small-text">Structured JD analysis will appear here after matching.</div>`;
    return;
  }

  const selected = results.filter((r) => r.selected).length;
  const average = results.reduce((sum, r) => sum + Number(r.score || 0), 0) / total;
  const top = normalizeResults(results)[0];
  const topName = top?.name || top?.email || top?.filename || "Candidate";
  const topScore = Math.round(Number(top?.score || 0) * 100);
  const jdPrefix = jdSummary ? `JD: ${jdSummary.slice(0, 80)}${jdSummary.length > 80 ? "..." : ""} | ` : "";

  summaryEl.textContent = `${jdPrefix}Top: ${topName} (${topScore}%). Selected: ${selected}/${total}. Avg score: ${Math.round(average * 100)}%.`;

  const role = jdAnalysis?.role || jdAnalysis?.role_category || "General role";
  const requiredSkills = Array.isArray(jdAnalysis?.required_skills) ? jdAnalysis.required_skills : [];
  const optionalSkills = Array.isArray(jdAnalysis?.optional_skills) ? jdAnalysis.optional_skills : [];
  const keywords = Array.isArray(jdAnalysis?.keywords) ? jdAnalysis.keywords : [];
  const minExperience = jdAnalysis?.minimum_experience_years;
  const education = Array.isArray(jdAnalysis?.education_requirements) ? jdAnalysis.education_requirements : [];

  jdPanel.innerHTML = `
    <div class="analysis-title">Job Analysis</div>
    <div class="analysis-grid">
      <div class="analysis-stat">
        <div class="analysis-stat-label">Role</div>
        <div class="analysis-stat-value">${escapeHtml(role)}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Category</div>
        <div class="analysis-stat-value">${escapeHtml(jdAnalysis?.role_category || "General")}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Min Experience</div>
        <div class="analysis-stat-value">${escapeHtml(minExperience != null ? `${minExperience} years` : "Not detected")}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Education</div>
        <div class="analysis-stat-value">${escapeHtml(education.length ? education.join(", ") : "Not specified")}</div>
      </div>
    </div>
    <div class="skill-section" style="margin-top:10px;">
      <div class="skill-title">Required Skills</div>
      <div class="skill-tags">${renderSkillTags(requiredSkills, "matched")}</div>
    </div>
    <div class="skill-section" style="margin-top:8px;">
      <div class="skill-title">Preferred Skills</div>
      <div class="skill-tags">${renderSkillTags(optionalSkills, "related")}</div>
    </div>
    <div class="skill-section" style="margin-top:8px;">
      <div class="skill-title">Keywords</div>
      <div class="skill-tags">${renderSkillTags(keywords, "neutral")}</div>
    </div>
  `;
}

function updateStatsSummary(stats) {
  const el = document.getElementById("stats-summary");
  if (!el) return;
  if (!stats) {
    el.textContent = "Stats not loaded yet.";
    return;
  }
  const avg = Math.round(Number(stats.average_score || 0) * 100);
  el.textContent = `History stats: total ${stats.total}, selected ${stats.selected}, rejected ${stats.rejected}, avg ${avg}%.`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSkillTags(skills, type = "neutral") {
  const className =
    type === "matched" ? "tag tag-matched" :
    type === "related" ? "tag tag-related" :
    type === "missing" ? "tag tag-missing" :
    "tag tag-neutral";
  if (!Array.isArray(skills) || !skills.length) {
    return `<span class="small-text">None</span>`;
  }
  return skills.map((s) => `<span class="${className}">${escapeHtml(s)}</span>`).join("");
}

function renderInterviewPanel(candidateId) {
  const panel = state.interviewQuestionsById[String(candidateId)] || {};
  const session = state.interviewSessionsByResumeId[String(candidateId)] || null;
  const sessionBlock = session
    ? `<div class="small-text">Interview: ${escapeHtml(session.status)} | Avg: ${escapeHtml(String(session.average_score || 0))}/10${session.current_question ? ` | Next: ${escapeHtml(session.current_question)}` : ""}</div>`
    : "";
  if (panel.loading) {
    return `<div class="interview-panel">${sessionBlock}<div class="small-text">Generating interview questions...</div></div>`;
  }
  if (!Array.isArray(panel.questions) || !panel.questions.length) {
    return `<div class="interview-panel">${sessionBlock}<div class="small-text">No interview questions generated yet.</div></div>`;
  }
  const list = panel.questions.map((q, idx) => `<li>${escapeHtml(`${idx + 1}. ${q}`)}</li>`).join("");
  const provider = panel.provider ? `<div class="small-text">Source: ${escapeHtml(panel.provider)}</div>` : "";
  return `
    <div class="interview-panel">
      ${sessionBlock}
      <div class="skill-title">Interview Questions</div>
      ${provider}
      <ol class="interview-list">${list}</ol>
    </div>
  `;
}

function renderResults() {
  const container = document.getElementById("results-container");
  const empty = document.getElementById("results-empty");
  const pageIndicator = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("btn-prev-page");
  const nextBtn = document.getElementById("btn-next-page");
  if (!container || !empty) return;

  const results = normalizeResults(state.results);
  const { pageItems, totalPages } = pagedResults(results);
  container.innerHTML = "";
  empty.style.display = results.length ? "none" : "block";
  if (pageIndicator) pageIndicator.textContent = `Page ${state.currentPage} / ${totalPages}`;
  if (prevBtn) prevBtn.disabled = state.currentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.currentPage >= totalPages;

  pageItems.forEach((cand) => {
    const scorePercent = Math.round(Number(cand.score || 0) * 100);
    const statusLabel = cand.selected ? "✔ Selected" : "✖ Not Selected";
    const allSkills = Array.isArray(cand.skills) ? cand.skills : [];
    const matchedSkills = Array.isArray(cand.matched_skills) ? cand.matched_skills : [];
    const relatedSkills = Array.isArray(cand.related_skills) ? cand.related_skills : [];
    const missingSkills = Array.isArray(cand.missing_skills) ? cand.missing_skills : [];
    const aiEvaluation = cand.ai_evaluation ? escapeHtml(cand.ai_evaluation).replaceAll("\n", "<br/>") : "";
    const idAttr = cand.id ? `data-resume-id="${cand.id}"` : "";
    const row = document.createElement("div");
    row.className = "leader-row";
    row.innerHTML = `
      <div class="leader-info">
        <div class="leader-name">${escapeHtml(cand.name || cand.email || cand.filename || "Candidate")}</div>
        <div class="leader-meta">${escapeHtml(cand.email || "No email")} | ${escapeHtml(cand.filename || "")}</div>
        <div class="leader-score-block">
          <div class="leader-score-title">Match Score: <strong>${scorePercent}%</strong></div>
          <div class="leader-status ${cand.selected ? "status-selected" : "status-not-selected"}">${statusLabel}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Skills</div>
          <div class="skill-tags">${renderSkillTags(allSkills, "neutral")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Matched Skills</div>
          <div class="skill-tags">${renderSkillTags(matchedSkills, "matched")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Related Skills</div>
          <div class="skill-tags">${renderSkillTags(relatedSkills, "related")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Missing Skills</div>
          <div class="skill-tags">${renderSkillTags(missingSkills, "missing")}</div>
        </div>
        ${aiEvaluation ? `<div class="skill-section"><div class="skill-title">AI Evaluation</div><div class="ai-eval">${aiEvaluation}</div></div>` : ""}
      </div>
      <div class="leader-actions" ${idAttr}>
        <button class="btn-chip btn-view">View</button>
        <button class="btn-chip btn-edit">Edit</button>
        <button class="btn-chip btn-delete">Delete</button>
        <button class="btn-chip btn-questions">Generate Interview Questions</button>
        <button class="btn-chip btn-start-interview">Start Interview</button>
        <button class="btn-chip btn-answer-interview">Submit Answer</button>
        <button class="btn-chip btn-finalize">Finalize</button>
        <button class="btn-chip btn-pick">Pick</button>
        <button class="btn-chip btn-row-slack">Slack</button>
        <button class="btn-chip btn-row-teams">Teams</button>
        <button class="btn-chip btn-row-ats">ATS</button>
      </div>
      ${cand.id ? renderInterviewPanel(cand.id) : ""}
    `;
    container.appendChild(row);
  });

  updateRankingSummary(state.results, state.lastPayload?.jd_summary || "");
}

function buildSummaryText() {
  if (!state.results.length) return "No results yet.";
  const lines = state.results
    .map((item, index) => {
      const score = Math.round(Number(item.score || 0) * 100);
      const label = item.name || item.email || item.filename || `Candidate ${index + 1}`;
      return `${index + 1}. ${label} - ${score}% - ${item.selected ? "Selected" : "Rejected"}`;
    })
    .join("\n");
  return `ResumeMatch Summary\nCandidates: ${state.results.length}\n\n${lines}`;
}

function openModal(title, content) {
  const modal = document.getElementById("resume-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalContent = document.getElementById("modal-content");
  if (!modal || !modalTitle || !modalContent) return;
  modalTitle.textContent = title;
  modalContent.textContent = content;
  modal.classList.remove("hidden");
}

function closeModal() {
  const modal = document.getElementById("resume-modal");
  if (!modal) return;
  modal.classList.add("hidden");
}

function startOnboarding() {
  const modal = document.getElementById("onboarding-modal");
  const titleEl = document.getElementById("onboarding-title");
  const bodyEl = document.getElementById("onboarding-body");
  const nextBtn = document.getElementById("btn-next-onboarding");
  const skipBtn = document.getElementById("btn-skip-onboarding");
  if (!modal || !titleEl || !bodyEl || !nextBtn || !skipBtn) return;
  if (localStorage.getItem("dashboard_onboarding_done") === "1") return;

  const steps = [
    { title: "Welcome to Dashboard", body: "Use Job Description + Upload to generate ranked candidates quickly." },
    { title: "History & Filters", body: "Load previous records and filter by email/name/min score in Candidate Ranking." },
    { title: "Manage Candidates", body: "Use View/Edit/Delete and pipeline APIs to move candidates through hiring stages." },
    { title: "Integrations + Demo", body: "Trigger Slack/Teams/ATS actions and use demo seed/reset for quick presentations." },
  ];
  let index = 0;
  const render = () => {
    const step = steps[index];
    titleEl.textContent = step.title;
    bodyEl.textContent = step.body;
    nextBtn.textContent = index === steps.length - 1 ? "Done" : "Next";
  };
  const close = () => {
    modal.classList.add("hidden");
    localStorage.setItem("dashboard_onboarding_done", "1");
  };
  nextBtn.onclick = () => {
    if (index >= steps.length - 1) {
      close();
      return;
    }
    index += 1;
    render();
  };
  skipBtn.onclick = close;

  render();
  modal.classList.remove("hidden");
}

function selectedResume() {
  return state.results.find((item) => Number(item.id) === Number(state.selectedResumeId)) || null;
}

function updateIntegrationTargetLabel() {
  const el = document.getElementById("integration-target");
  if (!el) return;
  const row = selectedResume();
  if (!row) {
    el.textContent = "No candidate selected.";
    return;
  }
  const label = row.name || row.email || row.filename || `ID ${row.id}`;
  el.textContent = `Selected: ${label} (ID ${row.id})`;
}

function pickResumeForIntegrations(resumeId) {
  state.selectedResumeId = Number(resumeId);
  const row = selectedResume();
  const msgBox = document.getElementById("integration-message");
  if (row && msgBox && !msgBox.value.trim()) {
    const label = row.name || row.email || row.filename || `resume ${row.id}`;
    msgBox.value = `Candidate update: ${label} is currently ${row.selected ? "selected" : "under review"}.`;
  }
  updateIntegrationTargetLabel();
}

function mapHistoryRecord(record) {
  const score = Number(record?.match_score || 0);
  const skills = Array.isArray(record?.required_skills) || Array.isArray(record?.matched_skills)
    ? Array.from(new Set([
        ...(Array.isArray(record?.matched_skills) ? record.matched_skills : []),
        ...((record?.tags || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)),
      ]))
    : (record?.tags || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
  return {
    id: record?.id || null,
    job_id: record?.job_id || null,
    filename: record?.filename || "",
    name: record?.name || null,
    email: record?.email || null,
    score,
    summary: record?.matched_job ? `Matched job: ${record.matched_job}` : "Saved history result",
    selected: score >= 0.6,
    selected_label: score >= 0.6 ? "Selected" : "Not Selected",
    skills,
    matched_skills: [],
    related_skills: [],
    missing_skills: [],
    required_skills: [],
    optional_skills: [],
    ai_evaluation: "",
  };
}

function buildSearchParamsFromInputs() {
  const jobId = document.getElementById("filter-job-id")?.value.trim();
  const email = document.getElementById("filter-email")?.value.trim();
  const name = document.getElementById("filter-name")?.value.trim();
  const minScoreRaw = document.getElementById("filter-min-score")?.value.trim();
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (email) params.set("email", email);
  if (name) params.set("name", name);
  if (minScoreRaw) params.set("min_score", minScoreRaw);
  params.set("limit", "200");
  return params;
}

function analyzeJobDescriptionText(jdText) {
  const stopWords = new Set([
    "the", "and", "for", "with", "you", "your", "are", "this", "that", "from", "have", "will", "our", "their",
    "but", "not", "all", "any", "can", "job", "role", "years", "year", "plus", "must", "should", "good", "strong",
    "etc", "into", "about", "has", "had", "who", "how", "what", "when", "where", "why", "they", "them", "his",
    "her", "she", "him", "its", "it's", "been", "being", "also", "able", "ability",
  ]);

  const tokens = (jdText.toLowerCase().match(/[a-z0-9+#.-]+/g) || []).filter((t) => t.length >= 2);
  const uniqueTokens = [...new Set(tokens)];
  const focusTerms = uniqueTokens.filter((t) => !stopWords.has(t) && !/^\d+$/.test(t)).slice(0, 12);
  const words = (jdText.trim().match(/\S+/g) || []).length;
  return { words, focusTerms };
}

async function fetchHistory(searchParams, parseMsg) {
  const token = getToken();
  if (!token) {
    setMessage(parseMsg, "Please log in first.", true);
    return;
  }
  const endpoint = searchParams ? `/resumes/search?${searchParams.toString()}` : "/resumes?limit=200";
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);

  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to load history."), true);
    return;
  }

  state.results = (result.payload || []).map(mapHistoryRecord);
  state.currentPage = 1;
  state.lastPayload = { results: state.results, jd_summary: "History records" };
  renderResults();
  setMessage(parseMsg, `Loaded ${state.results.length} historical record(s).`);
}

async function fetchStats(searchParams) {
  const token = getToken();
  if (!token) {
    updateStatsSummary(null);
    return;
  }
  const params = new URLSearchParams();
  const jobId = searchParams?.get("job_id");
  const minScore = searchParams?.get("min_score");
  if (jobId) params.set("job_id", jobId);
  if (minScore) params.set("min_score", minScore);
  const url = params.toString() ? `${API_BASE}/resumes/stats?${params.toString()}` : `${API_BASE}/resumes/stats`;

  const response = await fetch(url, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    updateStatsSummary(null);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    updateStatsSummary(null);
    return;
  }
  updateStatsSummary(result.payload);
}

async function uploadAndMatch() {
  const jdEl = document.getElementById("job-description");
  const msg = document.getElementById("parse-msg");
  const token = getToken();
  const jd = jdEl?.value.trim() || "";
  const selectedJobId = state.selectedJobId;

  if (!token) {
    setMessage(msg, "Please log in first.", true);
    return;
  }
  if (!jd && !selectedJobId) {
    setMessage(msg, "Please paste a job description or select a saved job.", true);
    return;
  }
  if (!state.selectedFiles.length) {
    setMessage(msg, "Please select at least one resume file.", true);
    return;
  }

  setMessage(msg, "Uploading and matching...");
  const form = new FormData();
  if (jd) form.append("job_description", jd);
  if (selectedJobId) form.append("job_id", String(selectedJobId));
  state.selectedFiles.forEach((file) => form.append("resumes", file));

  const response = await fetch(`${API_BASE}/resumes/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  }).catch(() => null);

  if (!response) {
    setMessage(msg, "Server error.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(msg, getErrorMessage(result.payload, `Error: ${result.status}`), true);
    return;
  }

  state.lastPayload = result.payload;
  state.results = result.payload.results || [];
  state.currentPage = 1;
  setMessage(msg, `Success. Processed ${result.payload.total_resumes || state.results.length} resume(s).`);
  renderResults();
  await fetchStats(null);
}

async function viewResumeById(resumeId, parseMsg) {
  const response = await fetch(`${API_BASE}/resumes/${resumeId}`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to load resume detail."), true);
    return;
  }
  const detail = result.payload;
  const local = state.results.find((item) => Number(item.id) === Number(resumeId)) || {};
  const score = Number(detail.match_score ?? local.score ?? 0);
  const selected = typeof local.selected === "boolean" ? local.selected : score >= 0.6;
  const selectedLabel = selected ? "Selected" : "Not Selected";
  const skills = Array.isArray(local.skills) ? local.skills : [];
  const matchedSkills = Array.isArray(local.matched_skills) ? local.matched_skills : [];
  const relatedSkills = Array.isArray(local.related_skills) ? local.related_skills : [];
  const missingSkills = Array.isArray(local.missing_skills) ? local.missing_skills : [];
  const requiredSkills = Array.isArray(local.required_skills) ? local.required_skills : [];
  const optionalSkills = Array.isArray(local.optional_skills) ? local.optional_skills : [];
  const aiEval = local.ai_evaluation || "";
  const preview = (detail.parsed_text || "").slice(0, 600);
  const message = [
    `Name: ${detail.name || "-"}`,
    `Email: ${detail.email || "-"}`,
    `Match Score: ${Math.round(score * 100)}%`,
    `Decision: ${selectedLabel}`,
    `Matched Job: ${detail.matched_job || "-"}`,
    "",
    `Skills: ${skills.length ? skills.join(", ") : "-"}`,
    `Matched Skills: ${matchedSkills.length ? matchedSkills.join(", ") : "-"}`,
    `Related Skills: ${relatedSkills.length ? relatedSkills.join(", ") : "-"}`,
    `Missing Skills: ${missingSkills.length ? missingSkills.join(", ") : "-"}`,
    `Required Skills (JD): ${requiredSkills.length ? requiredSkills.join(", ") : "-"}`,
    `Optional Skills (JD): ${optionalSkills.length ? optionalSkills.join(", ") : "-"}`,
    "",
    `AI Evaluation:`,
    aiEval || "-",
    "",
    `Text Preview:`,
    preview || "(no parsed text)",
  ].join("\n");
  openModal(`Resume #${resumeId}`, message);
}

function renderJobOptions() {
  const selectEl = document.getElementById("job-select");
  const filterSelectEl = document.getElementById("filter-job-id");
  if (!selectEl && !filterSelectEl) return;
  const selectedValue = state.selectedJobId != null ? String(state.selectedJobId) : "";
  const options = [
    `<option value="">Use pasted job description</option>`,
    ...state.jobs.map((job) => `<option value="${job.id}" ${String(job.id) === selectedValue ? "selected" : ""}>${escapeHtml(job.title)}</option>`),
  ];
  if (selectEl) {
    selectEl.innerHTML = options.join("");
  }
  if (filterSelectEl) {
    const currentFilterValue = filterSelectEl.value || "";
    const filterOptions = [
      `<option value="">All jobs</option>`,
      ...state.jobs.map((job) => `<option value="${job.id}" ${String(job.id) === String(currentFilterValue) ? "selected" : ""}>${escapeHtml(job.title)}</option>`),
    ];
    filterSelectEl.innerHTML = filterOptions.join("");
  }
}

function selectedJob() {
  return state.jobs.find((job) => Number(job.id) === Number(state.selectedJobId)) || null;
}

function applySelectedJobToEditor() {
  const jdEl = document.getElementById("job-description");
  const titleEl = document.getElementById("job-title");
  const job = selectedJob();
  if (!jdEl || !titleEl || !job) return;
  titleEl.value = job.title || "";
  jdEl.value = job.description || "";
  updateWordCount();
}

function renderJobsPanel() {
  const panel = document.getElementById("jobs-panel-list");
  if (!panel) return;
  if (!state.jobs.length) {
    panel.innerHTML = `<div class="small-text">No saved jobs yet.</div>`;
    return;
  }

  panel.innerHTML = state.jobs.map((job) => {
    const isSelected = Number(job.id) === Number(state.selectedJobId);
    const requiredSkills = Array.isArray(job.required_skills) ? job.required_skills : [];
    const optionalSkills = Array.isArray(job.optional_skills) ? job.optional_skills : [];
    return `
      <div class="job-card" data-job-id="${job.id}">
        <div class="job-card-header">
          <div>
            <div class="job-card-title">${escapeHtml(job.title || "Untitled job")}</div>
            <div class="job-card-meta">${escapeHtml(job.role_category || "General")} | ${escapeHtml(job.is_active ? "Active" : "Archived")}${isSelected ? " | Selected" : ""}</div>
          </div>
          <div class="job-card-actions">
            <button class="btn-chip btn-job-open">Open</button>
            <button class="btn-chip btn-job-edit">Edit</button>
            <button class="btn-chip btn-job-toggle">${job.is_active ? "Archive" : "Activate"}</button>
          </div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Required</div>
          <div class="skill-tags">${renderSkillTags(requiredSkills, "matched")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Preferred</div>
          <div class="skill-tags">${renderSkillTags(optionalSkills, "related")}</div>
        </div>
      </div>
    `;
  }).join("");
}

async function loadJobs(jobMsgEl, { silent = false } = {}) {
  const response = await fetch(`${API_BASE}/features/jobs`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);

  if (!response) {
    if (!silent) setMessage(jobMsgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    if (!silent) setMessage(jobMsgEl, getErrorMessage(result.payload, "Failed to load jobs."), true);
    return;
  }

  state.jobs = Array.isArray(result.payload) ? result.payload : [];
  if (state.selectedJobId != null && !selectedJob()) {
    state.selectedJobId = null;
  }
  renderJobOptions();
  renderJobsPanel();
  if (!silent) {
    setMessage(jobMsgEl, `Loaded ${state.jobs.length} saved job(s).`);
  }
}

async function saveCurrentJob(jobMsgEl) {
  const titleEl = document.getElementById("job-title");
  const jdEl = document.getElementById("job-description");
  const title = titleEl?.value.trim() || "";
  const description = jdEl?.value.trim() || "";
  if (!title || !description) {
    setMessage(jobMsgEl, "Enter both a job title and job description before saving.", true);
    return;
  }

  const response = await fetch(`${API_BASE}/features/jobs`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ title, description }),
  }).catch(() => null);

  if (!response) {
    setMessage(jobMsgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(jobMsgEl, getErrorMessage(result.payload, "Failed to save job."), true);
    return;
  }

  state.selectedJobId = result.payload.id;
  await loadJobs(jobMsgEl, { silent: true });
  renderJobOptions();
  renderJobsPanel();
  setMessage(jobMsgEl, `Saved job "${result.payload.title}".`);
}

async function updateJobRecord(jobId, payload, msgEl, successMessage) {
  const response = await fetch(`${API_BASE}/features/jobs/${jobId}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch(() => null);

  if (!response) {
    setMessage(msgEl, "Server not reachable.", true);
    return false;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(msgEl, getErrorMessage(result.payload, "Failed to update job."), true);
    return false;
  }

  await loadJobs(msgEl, { silent: true });
  renderJobOptions();
  renderJobsPanel();
  if (Number(state.selectedJobId) === Number(jobId)) {
    applySelectedJobToEditor();
  }
  setMessage(msgEl, successMessage);
  return true;
}

async function editResumeById(resumeId, parseMsg) {
  const current = state.results.find((item) => Number(item.id) === Number(resumeId));
  const newName = window.prompt("Candidate name", current?.name || "");
  if (newName === null) return;
  const newJob = window.prompt("Matched job title", current?.summary?.replace("Matched job: ", "") || "");
  if (newJob === null) return;
  const scoreInput = window.prompt("Match score (0 to 1)", String(Number(current?.score || 0).toFixed(2)));
  if (scoreInput === null) return;
  const parsedScore = Number(scoreInput);
  if (Number.isNaN(parsedScore) || parsedScore < 0 || parsedScore > 1) {
    setMessage(parseMsg, "Score must be a number between 0 and 1.", true);
    return;
  }

  const response = await fetch(`${API_BASE}/resumes/${resumeId}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({
      name: newName || null,
      matched_job: newJob || null,
      match_score: parsedScore,
    }),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Update failed."), true);
    return;
  }

  state.results = state.results.map((item) =>
    Number(item.id) === Number(resumeId)
      ? {
          ...item,
          name: result.payload.name,
          email: result.payload.email,
          score: Number(result.payload.match_score || 0),
          summary: result.payload.matched_job ? `Matched job: ${result.payload.matched_job}` : item.summary,
          selected: Number(result.payload.match_score || 0) >= 0.3,
        }
      : item
  );
  renderResults();
  setMessage(parseMsg, "Resume updated.");
}

async function deleteResumeById(resumeId, parseMsg) {
  const confirmed = window.confirm("Delete this resume record?");
  if (!confirmed) return;
  const response = await fetch(`${API_BASE}/resumes/${resumeId}`, {
    method: "DELETE",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Delete failed."), true);
    return;
  }
  state.results = state.results.filter((item) => Number(item.id) !== Number(resumeId));
  if (Number(state.selectedResumeId) === Number(resumeId)) {
    state.selectedResumeId = null;
    updateIntegrationTargetLabel();
  }
  state.currentPage = 1;
  renderResults();
  setMessage(parseMsg, "Resume deleted.");
}

async function generateInterviewQuestionsForResume(resumeId, parseMsg) {
  const key = String(resumeId);
  state.interviewQuestionsById[key] = { loading: true, questions: [] };
  renderResults();

  const response = await fetch(`${API_BASE}/features/resumes/${resumeId}/interview-questions`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    state.interviewQuestionsById[key] = { loading: false, questions: [] };
    renderResults();
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    state.interviewQuestionsById[key] = { loading: false, questions: [] };
    renderResults();
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to generate interview questions."), true);
    return;
  }
  const questions = Array.isArray(result.payload.questions) ? result.payload.questions : [];
  state.interviewQuestionsById[key] = {
    loading: false,
    questions,
    provider: result.payload.provider || "unknown",
  };
  renderResults();
  setMessage(parseMsg, "Interview questions generated.");
}

async function startInterviewForResume(resumeId, parseMsg) {
  const response = await fetch(`${API_BASE}/features/resumes/${resumeId}/interview/start`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ max_questions: 5, send_invitation_email: false }),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to start interview."), true);
    return;
  }
  state.interviewSessionsByResumeId[String(resumeId)] = result.payload;
  renderResults();
  setMessage(parseMsg, "Adaptive interview started.");
}

async function submitInterviewAnswerForResume(resumeId, parseMsg) {
  const session = state.interviewSessionsByResumeId[String(resumeId)];
  if (!session || !session.session_id) {
    setMessage(parseMsg, "Start the interview first.", true);
    return;
  }
  const promptText = session.current_question || "Enter candidate answer";
  const answerText = window.prompt(promptText, "");
  if (answerText === null || !answerText.trim()) return;
  const inputType = window.confirm("Treat this response as voice transcript?") ? "voice" : "text";

  const response = await fetch(`${API_BASE}/features/interviews/${session.session_id}/answer`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ answer_text: answerText.trim(), input_type: inputType }),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to submit interview answer."), true);
    return;
  }
  if (result.payload?.session) {
    state.interviewSessionsByResumeId[String(resumeId)] = result.payload.session;
  }
  renderResults();
  setMessage(parseMsg, `Interview answer scored ${result.payload.answer_score}/10.`);
}

async function finalizeResumeSelection(resumeId, parseMsg) {
  const response = await fetch(`${API_BASE}/features/resumes/${resumeId}/finalize-selection`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ send_email: false }),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to finalize selection."), true);
    return;
  }
  const current = state.results.find((item) => Number(item.id) === Number(resumeId));
  if (current) {
    current.final_score = result.payload.final_score;
    current.final_decision = result.payload.decision;
    current.selected = result.payload.decision === "selected";
    current.selected_label = result.payload.decision;
    current.score = Number(result.payload.final_score || current.score || 0);
  }
  renderResults();
  setMessage(parseMsg, `Final decision: ${result.payload.decision} (${Math.round(Number(result.payload.final_score || 0) * 100)}%).`);
}

async function sendNotification(provider, message, msgEl) {
  const endpoint = provider === "slack" ? "/features/notify/slack" : "/features/notify/teams";
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  }).catch(() => null);
  if (!response) {
    setMessage(msgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(msgEl, getErrorMessage(result.payload, "Notification failed."), true);
    return;
  }
  setMessage(msgEl, `${provider.toUpperCase()} notification sent.`);
}

async function syncSelectedResumeToAts(msgEl) {
  if (!state.selectedResumeId) {
    setMessage(msgEl, "Pick a candidate first.", true);
    return;
  }
  const response = await fetch(`${API_BASE}/features/integrations/ats-sync/${state.selectedResumeId}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ include_parsed_text: false }),
  }).catch(() => null);
  if (!response) {
    setMessage(msgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(msgEl, getErrorMessage(result.payload, "ATS sync failed."), true);
    return;
  }
  setMessage(msgEl, `ATS sync sent for resume ID ${state.selectedResumeId}.`);
}

async function seedDemoData(demoMsgEl, parseMsgEl) {
  const response = await fetch(`${API_BASE}/features/demo/seed`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ count: 8 }),
  }).catch(() => null);
  if (!response) {
    setMessage(demoMsgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(demoMsgEl, getErrorMessage(result.payload, "Demo seed failed."), true);
    return;
  }
  setMessage(demoMsgEl, `Created ${result.payload.created} demo candidates.`);
  await fetchHistory(null, parseMsgEl);
  await fetchStats(null);
}

async function resetDemoData(demoMsgEl, parseMsgEl) {
  const confirmed = window.confirm("This will remove all your resumes/templates/logs. Continue?");
  if (!confirmed) return;
  const response = await fetch(`${API_BASE}/features/demo/reset`, {
    method: "POST",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(demoMsgEl, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(demoMsgEl, getErrorMessage(result.payload, "Demo reset failed."), true);
    return;
  }
  setMessage(demoMsgEl, `Reset complete. Deleted ${result.payload.deleted.resumes} resumes.`);
  state.results = [];
  state.currentPage = 1;
  state.selectedResumeId = null;
  renderResults();
  updateIntegrationTargetLabel();
  await fetchStats(null);
  setMessage(parseMsgEl, "Data reset complete.");
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function renderBreakdownRows(scoreBreakdown = {}) {
  const rows = [
    ["Required", Number(scoreBreakdown.required_skill_score || 0)],
    ["Optional", Number(scoreBreakdown.optional_skill_score || 0)],
    ["Semantic", Number(scoreBreakdown.semantic_score || 0)],
    ["Experience", Number(scoreBreakdown.experience_score || 0)],
  ];
  return rows.map(([label, value]) => `
    <div class="score-row">
      <span>${escapeHtml(label)}</span>
      <div class="score-bar"><div class="score-bar-fill" style="width:${Math.max(0, Math.min(100, value * 100))}%"></div></div>
      <strong>${escapeHtml(formatPercent(value))}</strong>
    </div>
  `).join("");
}

function updateRankingSummary(results, jdSummary = "", jdAnalysis = null) {
  const summaryEl = document.getElementById("ranking-summary");
  const countEl = document.getElementById("dash-candidate-count");
  const jdPanel = document.getElementById("jd-analysis-panel");
  if (!summaryEl || !countEl || !jdPanel) return;

  const total = results.length;
  countEl.textContent = `${total} candidates loaded`;
  if (!total) {
    summaryEl.textContent = "No candidates yet. Run a match or load history.";
    jdPanel.innerHTML = `<div class="small-text">Structured JD analysis will appear here after matching.</div>`;
    return;
  }

  const selected = results.filter((r) => r.selected).length;
  const average = results.reduce((sum, r) => sum + Number(r.score || 0), 0) / total;
  const top = normalizeResults(results)[0];
  const topName = top?.name || top?.email || top?.filename || "Candidate";
  const topScore = Math.round(Number(top?.score || 0) * 100);
  const jdPrefix = jdSummary ? `JD: ${jdSummary.slice(0, 80)}${jdSummary.length > 80 ? "..." : ""} | ` : "";
  summaryEl.textContent = `${jdPrefix}Top: ${topName} (${topScore}%). Selected: ${selected}/${total}. Avg score: ${Math.round(average * 100)}%.`;

  const role = jdAnalysis?.role || jdAnalysis?.role_category || "General role";
  const requiredSkills = Array.isArray(jdAnalysis?.required_skills) ? jdAnalysis.required_skills : [];
  const optionalSkills = Array.isArray(jdAnalysis?.optional_skills) ? jdAnalysis.optional_skills : [];
  const keywords = Array.isArray(jdAnalysis?.keywords) ? jdAnalysis.keywords : [];
  const minExperience = jdAnalysis?.minimum_experience_years;
  const education = Array.isArray(jdAnalysis?.education_requirements) ? jdAnalysis.education_requirements : [];

  jdPanel.innerHTML = `
    <div class="analysis-title">Job Analysis</div>
    <div class="analysis-grid">
      <div class="analysis-stat">
        <div class="analysis-stat-label">Role</div>
        <div class="analysis-stat-value">${escapeHtml(role)}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Category</div>
        <div class="analysis-stat-value">${escapeHtml(jdAnalysis?.role_category || "General")}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Min Experience</div>
        <div class="analysis-stat-value">${escapeHtml(minExperience != null ? `${minExperience} years` : "Not detected")}</div>
      </div>
      <div class="analysis-stat">
        <div class="analysis-stat-label">Education</div>
        <div class="analysis-stat-value">${escapeHtml(education.length ? education.join(", ") : "Not specified")}</div>
      </div>
    </div>
    <div class="skill-section" style="margin-top:10px;">
      <div class="skill-title">Required Skills</div>
      <div class="skill-tags">${renderSkillTags(requiredSkills, "matched")}</div>
    </div>
    <div class="skill-section" style="margin-top:8px;">
      <div class="skill-title">Preferred Skills</div>
      <div class="skill-tags">${renderSkillTags(optionalSkills, "related")}</div>
    </div>
    <div class="skill-section" style="margin-top:8px;">
      <div class="skill-title">Keywords</div>
      <div class="skill-tags">${renderSkillTags(keywords, "neutral")}</div>
    </div>
  `;
}

function renderResults() {
  const container = document.getElementById("results-container");
  const empty = document.getElementById("results-empty");
  const pageIndicator = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("btn-prev-page");
  const nextBtn = document.getElementById("btn-next-page");
  if (!container || !empty) return;

  const results = normalizeResults(state.results);
  const { pageItems, totalPages } = pagedResults(results);
  container.innerHTML = "";
  empty.style.display = results.length ? "none" : "block";
  if (pageIndicator) pageIndicator.textContent = `Page ${state.currentPage} / ${totalPages}`;
  if (prevBtn) prevBtn.disabled = state.currentPage <= 1;
  if (nextBtn) nextBtn.disabled = state.currentPage >= totalPages;

  pageItems.forEach((cand) => {
    const scorePercent = Math.round(Number(cand.score || 0) * 100);
    const statusLabel = cand.selected ? "Selected" : "Not Selected";
    const allSkills = Array.isArray(cand.skills) ? cand.skills : [];
    const matchedSkills = Array.isArray(cand.matched_skills) ? cand.matched_skills : [];
    const relatedSkills = Array.isArray(cand.related_skills) ? cand.related_skills : [];
    const missingSkills = Array.isArray(cand.missing_skills) ? cand.missing_skills : [];
    const jdKeywords = Array.isArray(cand.jd_keywords) ? cand.jd_keywords : [];
    const scoreBreakdown = cand.score_breakdown && typeof cand.score_breakdown === "object" ? cand.score_breakdown : {};
    const semanticMode = scoreBreakdown.semantic_mode || "";
    const aiEvaluation = cand.ai_evaluation ? escapeHtml(cand.ai_evaluation).replaceAll("\n", "<br/>") : "";
    const idAttr = cand.id ? `data-resume-id="${cand.id}"` : "";
    const row = document.createElement("div");
    row.className = "leader-row";
    row.innerHTML = `
      <div class="leader-info">
        <div class="leader-name">${escapeHtml(cand.name || cand.email || cand.filename || "Candidate")}</div>
        <div class="leader-meta">${escapeHtml(cand.email || "No email")} | ${escapeHtml(cand.filename || "")}${cand.summary ? ` | ${escapeHtml(String(cand.summary).replace("Matched job: ", ""))}` : ""}</div>
        <div class="leader-score-block">
          <div class="leader-score-title">Match Score: <strong>${scorePercent}%</strong></div>
          <div class="leader-status ${cand.selected ? "status-selected" : "status-not-selected"}">${statusLabel}</div>
        </div>
        <div class="leader-insight-grid">
          <div class="leader-insight-card">
            <div class="skill-title">Role Fit</div>
            <div class="small-text">${escapeHtml(cand.role || cand.role_category || "General role")}</div>
          </div>
          <div class="leader-insight-card">
            <div class="skill-title">Semantic Mode</div>
            <div class="small-text">${escapeHtml(semanticMode || "Not available")}</div>
          </div>
        </div>
        ${Object.keys(scoreBreakdown).length ? `
          <div class="skill-section">
            <div class="skill-title">Score Breakdown</div>
            <div class="leader-insight-card">
              <div class="score-breakdown">${renderBreakdownRows(scoreBreakdown)}</div>
            </div>
          </div>
        ` : ""}
        <div class="skill-section">
          <div class="skill-title">Skills</div>
          <div class="skill-tags">${renderSkillTags(allSkills, "neutral")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Matched Skills</div>
          <div class="skill-tags">${renderSkillTags(matchedSkills, "matched")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Related Skills</div>
          <div class="skill-tags">${renderSkillTags(relatedSkills, "related")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">Missing Skills</div>
          <div class="skill-tags">${renderSkillTags(missingSkills, "missing")}</div>
        </div>
        <div class="skill-section">
          <div class="skill-title">JD Keywords</div>
          <div class="skill-tags">${renderSkillTags(jdKeywords, "neutral")}</div>
        </div>
        ${aiEvaluation ? `<div class="skill-section"><div class="skill-title">AI Evaluation</div><div class="ai-eval">${aiEvaluation}</div></div>` : ""}
      </div>
      <div class="leader-actions" ${idAttr}>
        <button class="btn-chip btn-view">View</button>
        <button class="btn-chip btn-edit">Edit</button>
        <button class="btn-chip btn-delete">Delete</button>
        <button class="btn-chip btn-questions">Generate Interview Questions</button>
        <button class="btn-chip btn-start-interview">Start Interview</button>
        <button class="btn-chip btn-answer-interview">Submit Answer</button>
        <button class="btn-chip btn-finalize">Finalize</button>
        <button class="btn-chip btn-pick">Pick</button>
        <button class="btn-chip btn-row-slack">Slack</button>
        <button class="btn-chip btn-row-teams">Teams</button>
        <button class="btn-chip btn-row-ats">ATS</button>
      </div>
      ${cand.id ? renderInterviewPanel(cand.id) : ""}
    `;
    container.appendChild(row);
  });

  updateRankingSummary(
    state.results,
    state.lastPayload?.jd_summary || "",
    state.lastPayload?.jd_analysis || null,
  );
}

function mapHistoryRecord(record) {
  const score = Number(record?.match_score || 0);
  const skills = (record?.tags || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return {
    id: record?.id || null,
    filename: record?.filename || "",
    name: record?.name || null,
    email: record?.email || null,
    score,
    summary: record?.matched_job ? `Matched job: ${record.matched_job}` : "Saved history result",
    selected: score >= 0.6,
    selected_label: score >= 0.6 ? "Selected" : "Not Selected",
    skills,
    matched_skills: Array.isArray(record?.matched_skills) ? record.matched_skills : [],
    related_skills: Array.isArray(record?.related_skills) ? record.related_skills : [],
    missing_skills: Array.isArray(record?.missing_skills) ? record.missing_skills : [],
    required_skills: Array.isArray(record?.required_skills) ? record.required_skills : [],
    optional_skills: Array.isArray(record?.optional_skills) ? record.optional_skills : [],
    role: record?.role || null,
    role_category: record?.role_category || null,
    jd_keywords: Array.isArray(record?.jd_keywords) ? record.jd_keywords : [],
    score_breakdown: record?.score_breakdown && typeof record.score_breakdown === "object" ? record.score_breakdown : {},
    ai_evaluation: record?.ai_evaluation || "",
  };
}

async function fetchHistory(searchParams, parseMsg) {
  const token = getToken();
  if (!token) {
    setMessage(parseMsg, "Please log in first.", true);
    return;
  }
  const endpoint = searchParams ? `/resumes/search?${searchParams.toString()}` : "/resumes?limit=200";
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);

  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to load history."), true);
    return;
  }

  state.results = (result.payload || []).map(mapHistoryRecord);
  state.currentPage = 1;
  state.lastPayload = { results: state.results, jd_summary: "History records", jd_analysis: null };
  renderResults();
  setMessage(parseMsg, `Loaded ${state.results.length} historical record(s).`);
}

async function viewResumeById(resumeId, parseMsg) {
  const response = await fetch(`${API_BASE}/resumes/${resumeId}`, {
    method: "GET",
    headers: authHeaders(),
  }).catch(() => null);
  if (!response) {
    setMessage(parseMsg, "Server not reachable.", true);
    return;
  }
  const result = await parseResponse(response);
  if (!result.ok) {
    handleUnauthorized(result.status);
    setMessage(parseMsg, getErrorMessage(result.payload, "Failed to load resume detail."), true);
    return;
  }
  const detail = result.payload;
  const local = state.results.find((item) => Number(item.id) === Number(resumeId)) || {};
  const score = Number(detail.match_score ?? local.score ?? 0);
  const selected = typeof local.selected === "boolean" ? local.selected : score >= 0.6;
  const selectedLabel = selected ? "Selected" : "Not Selected";
  const skills = Array.isArray(local.skills) ? local.skills : [];
  const matchedSkills = Array.isArray(local.matched_skills) ? local.matched_skills : [];
  const relatedSkills = Array.isArray(local.related_skills) ? local.related_skills : [];
  const missingSkills = Array.isArray(local.missing_skills) ? local.missing_skills : [];
  const requiredSkills = Array.isArray(local.required_skills) ? local.required_skills : [];
  const optionalSkills = Array.isArray(local.optional_skills) ? local.optional_skills : [];
  const jdKeywords = Array.isArray(local.jd_keywords) ? local.jd_keywords : [];
  const scoreBreakdown = local.score_breakdown && typeof local.score_breakdown === "object" ? local.score_breakdown : {};
  const aiEval = local.ai_evaluation || "";
  const preview = (detail.parsed_text || "").slice(0, 600);
  const message = [
    `Name: ${detail.name || "-"}`,
    `Email: ${detail.email || "-"}`,
    `Match Score: ${Math.round(score * 100)}%`,
    `Decision: ${selectedLabel}`,
    `Matched Job: ${detail.matched_job || "-"}`,
    `Role Fit: ${local.role || local.role_category || "-"}`,
    "",
    `Skills: ${skills.length ? skills.join(", ") : "-"}`,
    `Matched Skills: ${matchedSkills.length ? matchedSkills.join(", ") : "-"}`,
    `Related Skills: ${relatedSkills.length ? relatedSkills.join(", ") : "-"}`,
    `Missing Skills: ${missingSkills.length ? missingSkills.join(", ") : "-"}`,
    `Required Skills (JD): ${requiredSkills.length ? requiredSkills.join(", ") : "-"}`,
    `Optional Skills (JD): ${optionalSkills.length ? optionalSkills.join(", ") : "-"}`,
    `JD Keywords: ${jdKeywords.length ? jdKeywords.join(", ") : "-"}`,
    "",
    `Required Score: ${formatPercent(scoreBreakdown.required_skill_score)}`,
    `Optional Score: ${formatPercent(scoreBreakdown.optional_skill_score)}`,
    `Semantic Score: ${formatPercent(scoreBreakdown.semantic_score)}`,
    `Experience Score: ${formatPercent(scoreBreakdown.experience_score)}`,
    "",
    `AI Evaluation:`,
    aiEval || "-",
    "",
    `Text Preview:`,
    preview || "(no parsed text)",
  ].join("\n");
  openModal(`Resume #${resumeId}`, message);
}

function initDashboardPage() {
  const parseBtn = document.getElementById("btn-parse");
  if (!parseBtn) return;

  const jdEl = document.getElementById("job-description");
  const jobTitleEl = document.getElementById("job-title");
  const jobSelectEl = document.getElementById("job-select");
  const loadJobsBtn = document.getElementById("btn-load-jobs");
  const saveJobBtn = document.getElementById("btn-save-job");
  const jobMsg = document.getElementById("job-msg");
  const jobsPanelList = document.getElementById("jobs-panel-list");
  const jobsPanelMsg = document.getElementById("jobs-panel-msg");
  const refreshJobsPanelBtn = document.getElementById("btn-refresh-jobs-panel");
  const filesInput = document.getElementById("resumes");
  const uploadBox = document.getElementById("upload-box");
  const analyzeBtn = document.getElementById("btn-analyze");
  const clearBtn = document.getElementById("btn-clear-jd");
  const sortBtn = document.getElementById("btn-sort-score");
  const downloadBtn = document.getElementById("btn-download-json");
  const copyBtn = document.getElementById("btn-copy-summary");
  const exportMsg = document.getElementById("export-msg");
  const parseMsg = document.getElementById("parse-msg");
  const resultsContainer = document.getElementById("results-container");
  const prevPageBtn = document.getElementById("btn-prev-page");
  const nextPageBtn = document.getElementById("btn-next-page");
  const closeModalBtn = document.getElementById("btn-close-modal");
  const modal = document.getElementById("resume-modal");
  const loadHistoryBtn = document.getElementById("btn-load-history");
  const applyFiltersBtn = document.getElementById("btn-apply-filters");
  const logoutBtn = document.getElementById("btn-logout");
  const integrationMsg = document.getElementById("integration-msg");
  const integrationMessageInput = document.getElementById("integration-message");
  const sendSlackBtn = document.getElementById("btn-send-slack");
  const sendTeamsBtn = document.getElementById("btn-send-teams");
  const syncAtsBtn = document.getElementById("btn-sync-ats");
  const seedDemoBtn = document.getElementById("btn-seed-demo");
  const resetDemoBtn = document.getElementById("btn-reset-demo");
  const demoMsg = document.getElementById("demo-msg");

  jdEl?.addEventListener("input", updateWordCount);
  updateWordCount();

  filesInput?.addEventListener("change", () => {
    state.selectedFiles = Array.from(filesInput.files || []);
    renderFileList();
  });

  uploadBox?.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadBox.classList.add("dragover");
  });

  uploadBox?.addEventListener("dragleave", () => {
    uploadBox.classList.remove("dragover");
  });

  uploadBox?.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadBox.classList.remove("dragover");
    const dropped = Array.from(e.dataTransfer?.files || []);
    if (!dropped.length) return;
    state.selectedFiles = dropped;
    if (filesInput) {
      const dt = new DataTransfer();
      dropped.forEach((file) => dt.items.add(file));
      filesInput.files = dt.files;
    }
    renderFileList();
  });

  parseBtn.addEventListener("click", uploadAndMatch);

  analyzeBtn?.addEventListener("click", () => {
    const jd = jdEl?.value.trim() || "";
    if (!jd) {
      setMessage(parseMsg, "Paste a job description before analyze.", true);
      return;
    }
    const { words, focusTerms } = analyzeJobDescriptionText(jd);
    const rankingSummary = document.getElementById("ranking-summary");
    if (rankingSummary) {
      rankingSummary.textContent = focusTerms.length
        ? `JD analyzed: ${words} words. Key terms: ${focusTerms.join(", ")}.`
        : `JD analyzed: ${words} words. Add clearer skill keywords for better matching.`;
    }
    setMessage(parseMsg, `JD analyzed (${words} words). Now upload resumes and click Parse & Match.`);
  });

  clearBtn?.addEventListener("click", () => {
    if (jdEl) jdEl.value = "";
    if (jobTitleEl && !state.selectedJobId) jobTitleEl.value = "";
    state.selectedJobId = null;
    renderJobOptions();
    updateWordCount();
    setMessage(parseMsg, "Job description cleared.");
  });

  loadJobsBtn?.addEventListener("click", async () => {
    await loadJobs(jobMsg);
    if (jobsPanelMsg) setMessage(jobsPanelMsg, "Jobs refreshed.");
  });

  saveJobBtn?.addEventListener("click", async () => {
    await saveCurrentJob(jobMsg);
    if (jobsPanelMsg) setMessage(jobsPanelMsg, "Jobs panel updated.");
  });

  jobSelectEl?.addEventListener("change", () => {
    const rawValue = jobSelectEl.value;
    state.selectedJobId = rawValue ? Number(rawValue) : null;
    const currentJob = selectedJob();
    if (currentJob) {
      applySelectedJobToEditor();
      setMessage(jobMsg, `Selected saved job "${currentJob.title}".`);
    } else {
      setMessage(jobMsg, "Using pasted job description.");
    }
  });

  refreshJobsPanelBtn?.addEventListener("click", async () => {
    await loadJobs(jobsPanelMsg || jobMsg);
  });

  sortBtn?.addEventListener("click", () => {
    state.sortDescending = !state.sortDescending;
    sortBtn.textContent = state.sortDescending ? "Sort by score" : "Sort by score (asc)";
    renderResults();
  });

  prevPageBtn?.addEventListener("click", () => {
    state.currentPage -= 1;
    renderResults();
  });
  nextPageBtn?.addEventListener("click", () => {
    state.currentPage += 1;
    renderResults();
  });

  loadHistoryBtn?.addEventListener("click", async () => {
    await fetchHistory(null, parseMsg);
    await fetchStats(null);
  });

  closeModalBtn?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });

  applyFiltersBtn?.addEventListener("click", async () => {
    const params = buildSearchParamsFromInputs();
    await fetchHistory(params, parseMsg);
    await fetchStats(params);
  });

  logoutBtn?.addEventListener("click", () => {
    localStorage.removeItem("jwt_token");
    window.location.href = "login.html";
  });

  sendSlackBtn?.addEventListener("click", async () => {
    const message = integrationMessageInput?.value.trim() || "";
    if (!message) {
      setMessage(integrationMsg, "Enter a message for Slack.", true);
      return;
    }
    await sendNotification("slack", message, integrationMsg);
  });

  sendTeamsBtn?.addEventListener("click", async () => {
    const message = integrationMessageInput?.value.trim() || "";
    if (!message) {
      setMessage(integrationMsg, "Enter a message for Teams.", true);
      return;
    }
    await sendNotification("teams", message, integrationMsg);
  });

  syncAtsBtn?.addEventListener("click", async () => {
    await syncSelectedResumeToAts(integrationMsg);
  });

  seedDemoBtn?.addEventListener("click", async () => {
    await seedDemoData(demoMsg, parseMsg);
  });

  resetDemoBtn?.addEventListener("click", async () => {
    await resetDemoData(demoMsg, parseMsg);
  });

  resultsContainer?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const actionHost = target.closest("[data-resume-id]");
    if (!actionHost) return;
    const resumeId = actionHost.getAttribute("data-resume-id");
    if (!resumeId) return;
    if (target.classList.contains("btn-view")) {
      await viewResumeById(resumeId, parseMsg);
    } else if (target.classList.contains("btn-edit")) {
      await editResumeById(resumeId, parseMsg);
    } else if (target.classList.contains("btn-delete")) {
      await deleteResumeById(resumeId, parseMsg);
    } else if (target.classList.contains("btn-questions")) {
      await generateInterviewQuestionsForResume(resumeId, parseMsg);
    } else if (target.classList.contains("btn-start-interview")) {
      await startInterviewForResume(resumeId, parseMsg);
    } else if (target.classList.contains("btn-answer-interview")) {
      await submitInterviewAnswerForResume(resumeId, parseMsg);
    } else if (target.classList.contains("btn-finalize")) {
      await finalizeResumeSelection(resumeId, parseMsg);
    } else if (target.classList.contains("btn-pick")) {
      pickResumeForIntegrations(resumeId);
      setMessage(integrationMsg, `Picked resume ID ${resumeId} for integrations.`);
    } else if (target.classList.contains("btn-row-slack")) {
      pickResumeForIntegrations(resumeId);
      const message = integrationMessageInput?.value.trim() || `Candidate ${resumeId} status update.`;
      await sendNotification("slack", message, integrationMsg);
    } else if (target.classList.contains("btn-row-teams")) {
      pickResumeForIntegrations(resumeId);
      const message = integrationMessageInput?.value.trim() || `Candidate ${resumeId} status update.`;
      await sendNotification("teams", message, integrationMsg);
    } else if (target.classList.contains("btn-row-ats")) {
      pickResumeForIntegrations(resumeId);
      await syncSelectedResumeToAts(integrationMsg);
    }
  });

  jobsPanelList?.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const jobCard = target.closest("[data-job-id]");
    if (!jobCard) return;
    const jobId = Number(jobCard.getAttribute("data-job-id"));
    if (!jobId) return;
    const job = state.jobs.find((item) => Number(item.id) === jobId);
    if (!job) return;

    if (target.classList.contains("btn-job-open")) {
      state.selectedJobId = jobId;
      renderJobOptions();
      renderJobsPanel();
      applySelectedJobToEditor();
      setMessage(jobsPanelMsg, `Opened "${job.title}" in the editor.`);
    } else if (target.classList.contains("btn-job-edit")) {
      const newTitle = window.prompt("Job title", job.title || "");
      if (newTitle === null) return;
      const newDescription = window.prompt("Job description", job.description || "");
      if (newDescription === null) return;
      await updateJobRecord(
        jobId,
        { title: newTitle.trim(), description: newDescription.trim() },
        jobsPanelMsg || jobMsg,
        `Updated "${newTitle.trim() || job.title}".`,
      );
    } else if (target.classList.contains("btn-job-toggle")) {
      await updateJobRecord(
        jobId,
        { is_active: !job.is_active },
        jobsPanelMsg || jobMsg,
        `${job.is_active ? "Archived" : "Activated"} "${job.title}".`,
      );
    }
  });

  downloadBtn?.addEventListener("click", () => {
    if (!state.results.length) {
      setMessage(exportMsg, "No results to download.", true);
      return;
    }
    const content = JSON.stringify(state.lastPayload || { results: state.results }, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `resume-match-results-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setMessage(exportMsg, "JSON downloaded.");
  });

  copyBtn?.addEventListener("click", async () => {
    const text = buildSummaryText();
    try {
      await navigator.clipboard.writeText(text);
      setMessage(exportMsg, "Summary copied.");
    } catch {
      setMessage(exportMsg, "Clipboard not available in this browser context.", true);
    }
  });

  renderResults();
  updateIntegrationTargetLabel();
  startOnboarding();
  if (getToken()) {
    loadJobs(jobMsg, { silent: true });
    fetchHistory(null, parseMsg);
    fetchStats(null);
  } else {
    setMessage(parseMsg, "No active session. Redirecting to login...", true);
    setTimeout(() => {
      window.location.href = "login.html";
    }, 700);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginPage();
  initDashboardPage();
});
