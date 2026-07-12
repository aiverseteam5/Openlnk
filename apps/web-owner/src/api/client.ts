/**
 * API client for web-owner.
 *
 * TanStack Query hooks for commitment CRUD.
 * Cursor pagination only (CLAUDE.md).
 */

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1";

interface Commitment {
  id: string;
  context_id: string;
  owner_id: string;
  counterparty_id: string | null;
  title: string;
  class: string;
  amount_paise: number | null;
  currency: string;
  due_at: string | null;
  state: string;
  version: number;
  at_risk: boolean;
  provenance_kind: string | null;
  extraction_confidence: number | null;
  created_at: string;
  updated_at: string;
}

interface CursorPage {
  items: Commitment[];
  next_cursor: string | null;
  has_more: boolean;
}

interface Context {
  id: string;
  kind: string;
  household_id: string | null;
  business_id: string | null;
  label: string;
  created_at: string | null;
}

async function apiFetch<T>(
  path: string,
  opts: RequestInit = {},
  principalId?: string,
): Promise<T> {
  // Prefer Bearer token from localStorage, fall back to X-Principal-Id header
  const accessToken = localStorage.getItem("openlnk_access_token");
  const authHeader: Record<string, string> = accessToken
    ? { Authorization: `Bearer ${accessToken}` }
    : principalId
      ? { "X-Principal-Id": principalId }
      : {};

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeader,
    ...((opts.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  // On 401, try refreshing the token once
  if (res.status === 401 && accessToken) {
    const { useAppStore } = await import("../store/app");
    const refreshed = await useAppStore.getState().refreshAccessToken();
    if (refreshed) {
      // Retry with new token
      const newToken = localStorage.getItem("openlnk_access_token");
      const retryHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
        ...((opts.headers as Record<string, string>) ?? {}),
      };
      const retryRes = await fetch(`${API_BASE}${path}`, { ...opts, headers: retryHeaders });
      if (!retryRes.ok) {
        const body = await retryRes.text();
        throw new Error(`API ${retryRes.status}: ${body}`);
      }
      return retryRes.json();
    }
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export async function fetchCommitments(
  principalId: string,
  params: {
    context_id?: string;
    state?: string;
    cursor?: string;
    limit?: number;
  } = {},
): Promise<CursorPage> {
  const qs = new URLSearchParams();
  if (params.context_id) qs.set("context_id", params.context_id);
  if (params.state) qs.set("state", params.state);
  if (params.cursor) qs.set("cursor", params.cursor);
  if (params.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return apiFetch(`/commitments${query ? `?${query}` : ""}`, {}, principalId);
}

export async function fetchCommitment(
  principalId: string,
  id: string,
): Promise<Commitment> {
  return apiFetch(`/commitments/${id}`, {}, principalId);
}

export async function fetchContexts(
  principalId: string,
): Promise<Context[]> {
  return apiFetch("/contexts", {}, principalId);
}

export async function transitionState(
  principalId: string,
  id: string,
  newState: string,
  version: number,
): Promise<Commitment> {
  return apiFetch(
    `/commitments/${id}/state`,
    {
      method: "PATCH",
      body: JSON.stringify({ new_state: newState, version }),
      headers: { "Idempotency-Key": self.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}` },
    },
    principalId,
  );
}

export interface AuditEntry {
  id: number;
  at: string;
  actor_kind: string;
  event: string;
  detail: Record<string, unknown>;
}

export async function fetchCommitmentHistory(
  principalId: string,
  id: string,
): Promise<AuditEntry[]> {
  return apiFetch(`/commitments/${id}/history`, {}, principalId);
}

export async function correctCommitment(
  principalId: string,
  id: string,
  body: { action: string; edits?: Record<string, unknown> },
): Promise<Commitment> {
  return apiFetch(
    `/commitments/${id}/correct`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
    principalId,
  );
}

export type { Commitment, CursorPage, Context };
