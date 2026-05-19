import { apiFetch } from "@/api/client";
import type { AiSummary, Resume, ResumeChunk, ResumeStats } from "@/api/types";

export type ResumeSearchParams = {
  query?: string;
  min_score?: number;
  max_score?: number;
  date_from?: string;
  date_to?: string;
};

export function listResumes() {
  return apiFetch<Resume[]>("/resumes");
}

export function searchResumes(params: ResumeSearchParams) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return apiFetch<Resume[]>(`/resumes/search?${query.toString()}`);
}

export function getResume(id: number) {
  return apiFetch<Resume>(`/resumes/${id}`);
}

export function getResumeStats() {
  return apiFetch<ResumeStats>("/resumes/stats");
}

export function getAiSummary(id: number) {
  return apiFetch<AiSummary>(`/features/resumes/${id}/ai-summary`);
}

export function getResumeChunks(id: number) {
  return apiFetch<ResumeChunk[]>(`/features/resumes/${id}/chunks`);
}

export function updateResumeNotes(id: number, notes: string) {
  return apiFetch<{ id: number; notes: string }>(`/features/resumes/${id}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

export function updateStage(id: number, stage: string) {
  return apiFetch<Resume>(`/features/resumes/${id}/stage`, {
    method: "PATCH",
    body: JSON.stringify({ stage }),
  });
}
