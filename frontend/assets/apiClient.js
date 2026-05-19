const API_BASE = localStorage.getItem("api_base") || window.location.origin;

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (response.ok) {
    return data;
  }
  if (typeof data?.detail === "string" && data.detail.trim()) {
    return data.detail;
  }
  return `Request failed (${response.status})`;
}

export async function signup(payload) {
  const response = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function login(payload) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function register(payload) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function uploadResumes({
  token,
  files = [],
  jdText,
  jdFile,
}) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (jdText) {
    formData.append("jd_text", jdText);
  }
  if (jdFile) {
    formData.append("jd_file", jdFile);
  }

  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${API_BASE}/resumes/upload`, {
    method: "POST",
    headers,
    body: formData,
  });
  return parseResponse(response);
}

export { API_BASE };
