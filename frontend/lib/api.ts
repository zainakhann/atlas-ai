export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("atlas_token");
}

export function setToken(token: string) {
  localStorage.setItem("atlas_token", token);
}

export function clearToken() {
  localStorage.removeItem("atlas_token");
  localStorage.removeItem("atlas_is_demo");
}

export function setIsDemo(value: boolean) {
  if (value) localStorage.setItem("atlas_is_demo", "true");
  else localStorage.removeItem("atlas_is_demo");
}

export function isDemoAccount(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("atlas_is_demo") === "true";
}

export function notifyConversationsChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("atlas:conversations-changed"));
  }
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
  }

  return response;
}