/**
 * App store — Zustand (CLAUDE.md: Zustand for local state).
 *
 * Server state lives in TanStack Query. This store holds
 * client-only UI state: filters, selected context, auth tokens.
 */

import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import type { CommitmentState } from "@openlnk/ui";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

interface AppState {
  // Auth
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  authLoading: boolean;

  // Principal
  principalId: string;

  // UI state
  selectedContextId: string | null;
  stateFilter: CommitmentState | null;

  // Actions
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  restoreSession: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  setPrincipalId: (id: string) => void;
  setSelectedContextId: (id: string | null) => void;
  setStateFilter: (state: CommitmentState | null) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  authLoading: true,

  principalId: "00000000-0000-0000-0000-000000000001",

  selectedContextId: null,
  stateFilter: null,

  login: (accessToken, refreshToken) => {
    void SecureStore.setItemAsync("openlnk_access_token", accessToken);
    void SecureStore.setItemAsync("openlnk_refresh_token", refreshToken);
    const payload = parseJwtPayload(accessToken);
    set({
      accessToken,
      refreshToken,
      isAuthenticated: true,
      principalId: (payload?.sub as string) ?? "",
    });
  },

  logout: () => {
    void SecureStore.deleteItemAsync("openlnk_access_token");
    void SecureStore.deleteItemAsync("openlnk_refresh_token");
    set({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      principalId: "00000000-0000-0000-0000-000000000001",
    });
  },

  restoreSession: async () => {
    try {
      const accessToken = await SecureStore.getItemAsync("openlnk_access_token");
      const refreshToken = await SecureStore.getItemAsync("openlnk_refresh_token");
      if (accessToken && refreshToken) {
        const payload = parseJwtPayload(accessToken);
        set({
          accessToken,
          refreshToken,
          isAuthenticated: true,
          authLoading: false,
          principalId: (payload?.sub as string) ?? "",
        });
      } else {
        set({ authLoading: false });
      }
    } catch {
      set({ authLoading: false });
    }
  },

  refreshAccessToken: async () => {
    const { refreshToken } = get();
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API_BASE}/v1/auth/refresh`, {
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

  setPrincipalId: (id) => set({ principalId: id }),
  setSelectedContextId: (id) => set({ selectedContextId: id }),
  setStateFilter: (state) => set({ stateFilter: state }),
}));
