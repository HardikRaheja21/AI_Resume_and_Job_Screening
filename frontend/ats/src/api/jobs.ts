import { apiFetch } from "@/api/client";
import type { Job } from "@/api/types";

export type JobPayload = {
  title: string;
  description: string;
};

export function listJobs() {
  return apiFetch<Job[]>("/features/jobs");
}

export function createJob(payload: JobPayload) {
  return apiFetch<Job>("/features/jobs", { method: "POST", body: JSON.stringify(payload) });
}

export function updateJob(id: number, payload: Partial<JobPayload> & { is_active?: boolean }) {
  return apiFetch<Job>(`/features/jobs/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function archiveJob(id: number) {
  return updateJob(id, { is_active: false });
}
