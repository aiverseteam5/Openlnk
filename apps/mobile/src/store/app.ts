/**
 * App store — Zustand (CLAUDE.md: Zustand for local state).
 *
 * Server state lives in TanStack Query. This store holds
 * client-only UI state: filters, selected context, principal.
 */

import { create } from "zustand";
import type { CommitmentState } from "@openlnk/ui";

interface AppState {
  principalId: string;
  selectedContextId: string | null;
  stateFilter: CommitmentState | null;

  setPrincipalId: (id: string) => void;
  setSelectedContextId: (id: string | null) => void;
  setStateFilter: (state: CommitmentState | null) => void;
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
