import { useAuthContext } from "@/auth/AuthProvider";

export function useAuth() {
  return useAuthContext();
}
