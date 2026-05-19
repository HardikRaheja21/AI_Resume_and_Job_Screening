import { Navigate } from "react-router-dom";
import type { UserRole } from "@/api/types";
import { useAuth } from "@/auth/useAuth";

export function RequireRole({ allowed, children }: { allowed: UserRole[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user || !allowed.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}
