import { apiFetch } from "@/api/client";

export function seedDemoData(count = 15) {
  return apiFetch<{ created: number }>(`/features/demo/seed`, {
    method: "POST",
    body: JSON.stringify({ count }),
  });
}

export function resetDemoData() {
  return apiFetch<{ reset: boolean }>(`/features/demo/reset`, {
    method: "POST",
  });
}
