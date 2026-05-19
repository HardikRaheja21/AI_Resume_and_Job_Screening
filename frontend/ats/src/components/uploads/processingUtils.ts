import type { ProcessingEvent, ProcessingJob } from "@/api/types";
import { PROCESSING_STEPS } from "@/lib/constants";

export type UploadStatus = "queued" | "running" | "retrying" | "completed" | "failed";

export function normalizeStatus(status?: string): UploadStatus {
  const normalized = (status || "queued").toLowerCase();
  if (normalized.includes("complete") || normalized === "success") return "completed";
  if (normalized.includes("fail") || normalized.includes("error")) return "failed";
  if (normalized.includes("retry")) return "retrying";
  if (normalized.includes("run") || normalized.includes("process")) return "running";
  return "queued";
}

export function getStageIndex(job?: Pick<ProcessingJob, "status" | "current_step">) {
  if (!job) return 0;
  const status = normalizeStatus(job.status);
  if (status === "completed") return PROCESSING_STEPS.length - 1;
  const step = (job.current_step || "").toLowerCase();
  if (step.includes("ocr")) return 2;
  if (step.includes("skill") || step.includes("extract")) return 3;
  if (step.includes("match") || step.includes("score")) return 4;
  if (step.includes("embed") || step.includes("vector")) return 5;
  if (step.includes("ai") || step.includes("summary")) return 6;
  if (step.includes("parse") || step.includes("parsing")) return 1;
  return status === "running" ? 1 : 0;
}

export function getLatestEventMessage(events?: ProcessingEvent[]) {
  const latest = [...(events || [])].reverse().find((event) => event.message || event.step || event.status);
  if (!latest) return "Waiting for processing events...";
  return latest.message || `${latest.step}: ${latest.status}`;
}

export function getDuration(start?: string | null, end?: string | null) {
  const started = start ? new Date(start).getTime() : Date.now();
  const finished = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(started) || Number.isNaN(finished)) return "0s";
  const seconds = Math.max(0, Math.round((finished - started) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${rest}s`;
}

export function isTerminal(status?: string) {
  const normalized = normalizeStatus(status);
  return normalized === "completed" || normalized === "failed";
}

export function averageProgress(jobs: ProcessingJob[]) {
  if (!jobs.length) return 0;
  return Math.round(jobs.reduce((sum, job) => sum + (job.progress || 0), 0) / jobs.length);
}
