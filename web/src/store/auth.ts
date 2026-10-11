import { create } from "zustand";

import { api, ApiError, setToken } from "../api/client";
import type { AuthResponse, User } from "../api/types";

const STORAGE_KEY = "driftboard.auth";

interface AuthState {
  user: User | null;
  token: string | null;
  error: string | null;
  busy: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

function loadStored(): { user: User; token: string } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const stored = loadStored();
if (stored) setToken(stored.token);

export const useAuth = create<AuthState>((set) => {
  const finish = (res: AuthResponse) => {
    setToken(res.access_token);
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ user: res.user, token: res.access_token }),
    );
    set({ user: res.user, token: res.access_token, error: null, busy: false });
  };
  const fail = (err: unknown) =>
    set({ busy: false, error: err instanceof ApiError ? err.message : "Something went wrong" });

  return {
    user: stored?.user ?? null,
    token: stored?.token ?? null,
    error: null,
    busy: false,

    async login(email, password) {
      set({ busy: true, error: null });
      try {
        finish(await api.post<AuthResponse>("/api/auth/login", { email, password }));
      } catch (err) {
        fail(err);
      }
    },

    async register(email, username, password) {
      set({ busy: true, error: null });
      try {
        finish(await api.post<AuthResponse>("/api/auth/register", { email, username, password }));
      } catch (err) {
        fail(err);
      }
    },

    logout() {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
      set({ user: null, token: null });
    },
  };
});
