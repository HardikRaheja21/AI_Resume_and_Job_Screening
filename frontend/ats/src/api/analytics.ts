import { apiFetch } from "@/api/client";

export type FunnelItem = { stage: string; count: number };

export function getFunnel() {
  return apiFetch<FunnelItem[]>("/features/analytics/funnel");
}
