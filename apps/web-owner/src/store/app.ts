/**
 * Local state store (Zustand). Server state via TanStack Query.
 *
 * CLAUDE.md: TanStack Query for server state, Zustand for local state.
 */

import { create } from "zustand";

interface AppState {
  principalId: string;
  selectedContextId: string | null;
  stateFilter: string | null;
  setPrincipalId: (id: string) => void;
  setSelectedContextId: (id: string | null) => void;
  setStateFilter: (state: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Placeholder — replaced by auth at Gate 2
  principalId: "00000000-0000-0000-0000-000000000001",
  selectedContextId: null,
  stateFilter: null,
  setPrincipalId: (id) => set({ principalId: id }),
  setSelectedContextId: (id) => set({ selectedContextId: id }),
  setStateFilter: (state) => set({ stateFilter: state }),
}));
