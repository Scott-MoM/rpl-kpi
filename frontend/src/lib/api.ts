function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }

  if (import.meta.env.DEV) {
    return "http://localhost:8000/api";
  }

  throw new Error("VITE_API_BASE_URL is not configured.");
}

const API_BASE_URL = resolveApiBaseUrl();
const TOKEN_STORAGE_KEY = "rpl-kpi-token";
const USER_STORAGE_KEY = "rpl-kpi-user";

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function getStoredUser<T>() {
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  return raw ? (JSON.parse(raw) as T) : null;
}

export function setStoredUser<T>(user: T) {
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredUser() {
  window.localStorage.removeItem(USER_STORAGE_KEY);
}

type RequestOptions = RequestInit & {
  token?: string | null;
};

export async function fetchJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...rest } = options;
  const authToken = token ?? getStoredToken();
  const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...headers
    }
  });

  if (!response.ok) {
    let detail = `API request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // Ignore non-JSON errors.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
