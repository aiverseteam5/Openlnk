/**
 * Local state store (Zustand). Server state via TanStack Query.
 *
 * CLAUDE.md: TanStack Query for server state, Zustand for local state.
 */

import { create } from "zustand";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

interface AppState {
  // Auth
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  // Principal (derived from JWT or dev header)
  principalId: string;

  // UI state
  selectedContextId: string | null;
  stateFilter: string | null;

  // Actions
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  setPrincipalId: (id: string) => void;
  setSelectedContextId: (id: string | null) => void;
  setStateFilter: (state: string | null) => void;
  refreshAccessToken: () => Promise<boolean>;
}

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

// Restore from localStorage on init
const storedAccess = localStorage.getItem("openlnk_access_token");
const storedRefresh = localStorage.getItem("openlnk_refresh_token");
const storedPrincipal = storedAccess
  ? (parseJwtPayload(storedAccess)?.sub as string) ?? ""
  : "";

export const useAppStore = create<AppState>((set, get) => ({
  accessToken: storedAccess,
  refreshToken: storedRefresh,
  isAuthenticated: !!storedAccess,

  // If we have a JWT, extract principal from it; otherwise use dev placeholder
  principalId: storedPrincipal || "00000000-0000-0000-0000-000000000001",

  selectedContextId: null,
  stateFilter: null,

  login: (accessToken, refreshToken) => {
    localStorage.setItem("openlnk_access_token", accessToken);
    localStorage.setItem("openlnk_refresh_token", refreshToken);
    const payload = parseJwtPayload(accessToken);
    const principalId = (payload?.sub as string) ?? "";
    set({
      accessToken,
      refreshToken,
      isAuthenticated: true,
      principalId,
    });
  },

  logout: () => {
    localStorage.removeItem("openlnk_access_token");
    localStorage.removeItem("openlnk_refresh_token");
    set({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      principalId: "00000000-0000-0000-0000-000000000001",
    });
  },

  setPrincipalId: (id) => set({ principalId: id }),
  setSelectedContextId: (id) => set({ selectedContextId: id }),
  setStateFilter: (state) => set({ stateFilter: state }),

  refreshAccessToken: async () => {
    const { refreshToken } = get();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        get().logout();
        return false;
      }
      const tokens = await res.json();
      get().login(tokens.access_token, tokens.refresh_token);
      return true;
    } catch {
      get().logout();
      return false;
    }
  },
}));
