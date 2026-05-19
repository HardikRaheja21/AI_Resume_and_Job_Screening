import { apiFetch, API_BASE_URL, getStoredToken } from "@/api/client";
import type { AsyncUploadResponse, ProcessingEvent, ProcessingJob } from "@/api/types";

export function uploadResumes(files: File[], jobId?: number, jdText?: string) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  if (jobId) form.append("job_id", String(jobId));
  if (jdText) form.append("jd_text", jdText);
  return apiFetch<AsyncUploadResponse>("/processing/resumes/upload", { method: "POST", body: form });
}

export function getProcessingJob(id: number) {
  return apiFetch<ProcessingJob>(`/processing/jobs/${id}`);
}

export function getProcessingEvents(id: number) {
  return apiFetch<ProcessingEvent[]>(`/processing/jobs/${id}/events`);
}

export function enqueueResumeProcessing(resumeId: number, jobId?: number) {
  const query = new URLSearchParams();
  if (jobId) query.set("job_id", String(jobId));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<{ processing_job: ProcessingJob }>(`/processing/resumes/${resumeId}/enqueue${suffix}`, {
    method: "POST",
  });
}

export function openProcessingStream(id: number) {
  const token = getStoredToken();
  const url = new URL(`${API_BASE_URL}/processing/jobs/${id}/stream`);
  if (token) url.searchParams.set("token", token);
  return new EventSource(url.toString());
}

export function getProcessingStreamUrl(id: number) {
  return `${API_BASE_URL}/processing/jobs/${id}/stream`;
}

export function getProcessingAuthHeaders(): HeadersInit {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
