import { createContext, PropsWithChildren, useContext, useEffect, useState } from "react";

import {
  ApiError,
  clearStoredToken,
  clearStoredUser,
  fetchJson,
  getStoredToken,
  getStoredUser,
  setStoredToken,
  setStoredUser
} from "../lib/api";

export type UserSession = {
  email: string;
  name: string;
  role: string;
  roles: string[];
  region: string;
  force_password_change: boolean;
};

type LoginResponse = {
  user: UserSession;
  access_token: string;
  token_type: string;
};

type SessionContextValue = {
  user: UserSession | null;
  token: string | null;
  isReady: boolean;
  login: (email: string, password: string) => Promise<UserSession>;
  logout: () => void;
  changePassword: (temporaryPassword: string, newPassword: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<string>;
  refreshUser: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<UserSession | null>(() => getStoredUser<UserSession>());
  const [isReady, setIsReady] = useState(false);

  async function refreshUser() {
    const existingToken = getStoredToken();
    if (!existingToken) {
      setUser(null);
      return;
    }
    const currentUser = await fetchJson<UserSession>("/auth/me", { token: existingToken });
    setUser(currentUser);
    setStoredUser(currentUser);
  }

  useEffect(() => {
    const existingToken = getStoredToken();
    if (!existingToken) {
      setIsReady(true);
      return;
    }

    refreshUser()
      .catch((error) => {
        if (error instanceof ApiError && error.status && [401, 403].includes(error.status)) {
          clearStoredToken();
          clearStoredUser();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => setIsReady(true));
  }, []);

  async function login(email: string, password: string) {
    const response = await fetchJson<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    setToken(response.access_token);
    setUser(response.user);
    setStoredToken(response.access_token);
    setStoredUser(response.user);
    return response.user;
  }

  async function changePassword(temporaryPassword: string, newPassword: string) {
    if (!user) {
      throw new Error("No authenticated user.");
    }
    await fetchJson<{ status: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        email: user.email,
        temporary_password: temporaryPassword,
        new_password: newPassword
      })
    });
    await refreshUser();
  }

  async function requestPasswordReset(email: string) {
    const response = await fetchJson<{ status: string }>("/auth/password-reset-request", {
      method: "POST",
      body: JSON.stringify({ email })
    });
    return response.status;
  }

  function logout() {
    clearStoredToken();
    clearStoredUser();
    setToken(null);
    setUser(null);
  }

  return (
    <SessionContext.Provider value={{ user, token, isReady, login, logout, changePassword, requestPasswordReset, refreshUser }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return context;
}
