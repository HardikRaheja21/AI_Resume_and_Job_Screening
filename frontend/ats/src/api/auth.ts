import { apiFetch } from "@/api/client";
import type { TokenResponse, User } from "@/api/types";

export type AuthPayload = {
  email: string;
  password: string;
  full_name?: string;
};

export function login(payload: AuthPayload) {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: payload.email, password: payload.password }),
    auth: false,
  });
}

export function register(payload: AuthPayload) {
  return apiFetch<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    auth: false,
  });
}

export function getMe() {
  return apiFetch<User>("/auth/me");
}
