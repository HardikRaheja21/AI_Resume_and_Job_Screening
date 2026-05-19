import type { UserRole } from "@/api/types";

export function canAccessAdmin(role?: UserRole) {
  return role === "admin";
}
