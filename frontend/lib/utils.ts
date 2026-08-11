import { clearToken, getToken } from "@/lib/auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws/live";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    });
  } catch {
    throw new Error(`Cannot reach backend at ${API_URL}. Start the backend first.`);
  }
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Session expired — please log in again.");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

/**
 * The backend sends naive UTC timestamps with no timezone suffix (e.g.
 * "2026-08-11T04:10:00"). `new Date(...)` parses a string like that as
 * local browser time, not UTC — silently wrong unless the browser's OS
 * timezone happens to be UTC. Always use this instead of `new Date(iso)`
 * for any timestamp field coming from the API.
 */
export function parseUtcDate(iso: string): Date {
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(iso);
  return new Date(hasTimezone ? iso : `${iso}Z`);
}
